

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        String input_1_0 = String.valueOf(args[0]);
        String input_2_0 = String.valueOf(args[1]);


        // Perform computation         
        String output_1 = input_1_0.toString();
        String output_2 = input_2_0.toString();

        
        // Compare output
        if (output_1.equals("") && output_2.equals("<N}C2<]j")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

