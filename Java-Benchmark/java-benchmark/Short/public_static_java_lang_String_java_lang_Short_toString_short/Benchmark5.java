

public class Benchmark5 {
    public static void main(String[] args) {
        // fetch input
        Short input_1_0 = Short.valueOf(args[0]);
        Short input_2_0 = Short.valueOf(args[1]);


        // Perform computation         
        String output_1 = Short.toString(input_1_0);
        String output_2 = Short.toString(input_2_0);

        
        // Compare output
        if (output_1.equals("2384") && output_2.equals("8558")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

