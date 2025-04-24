

public class Benchmark1 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        String output_1 = input_1_0.toString();
        String output_2 = input_2_0.toString();

        
        // Compare output
        if (output_1.equals("-3.5147154783890335E147") && output_2.equals("4.344860347452421E112")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

